"""
Response streaming for better perceived performance in Streamlit
"""

import time
import threading
import queue
import logging
from typing import Iterator, Generator, Any, Dict, Optional
import streamlit as st

logger = logging.getLogger(__name__)

class ResponseStreamer:
    """Handles streaming responses for better user experience"""
    
    def __init__(self, container, chunk_size: int = 50, delay: float = 0.05):
        self.container = container
        self.chunk_size = chunk_size
        self.delay = delay
        self.current_text = ""
        self.is_streaming = False
        self.stream_thread = None
        self.stop_event = threading.Event()
    
    def start_streaming(self, full_response: str, placeholder=None):
        """Start streaming a response"""
        if self.is_streaming:
            self.stop_streaming()
        
        self.is_streaming = True
        self.stop_event.clear()
        self.current_text = ""
        
        if placeholder is None:
            placeholder = self.container.empty()
        
        # Start streaming in a separate thread
        self.stream_thread = threading.Thread(
            target=self._stream_response,
            args=(full_response, placeholder),
            daemon=True
        )
        self.stream_thread.start()
        
        return placeholder
    
    def _stream_response(self, full_response: str, placeholder):
        """Stream response character by character"""
        try:
            for i in range(0, len(full_response), self.chunk_size):
                if self.stop_event.is_set():
                    break
                
                chunk = full_response[i:i + self.chunk_size]
                self.current_text += chunk
                
                # Update the placeholder with current text
                placeholder.markdown(self.current_text + "▌")  # Cursor effect
                
                time.sleep(self.delay)
            
            # Final update without cursor
            if not self.stop_event.is_set():
                placeholder.markdown(self.current_text)
                self.is_streaming = False
                
        except Exception as e:
            logger.error(f"❌ Streaming error: {e}")
            placeholder.error(f"Error streaming response: {e}")
            self.is_streaming = False
    
    def stop_streaming(self):
        """Stop the current streaming operation"""
        if self.is_streaming:
            self.stop_event.set()
            if self.stream_thread and self.stream_thread.is_alive():
                self.stream_thread.join(timeout=1.0)
            self.is_streaming = False
    
    def get_current_text(self) -> str:
        """Get the currently streamed text"""
        return self.current_text

class TypingIndicator:
    """Shows typing indicator while processing"""
    
    def __init__(self, container, message: str = "Thinking..."):
        self.container = container
        self.message = message
        self.placeholder = None
        self.is_active = False
        self.thread = None
        self.stop_event = threading.Event()
    
    def start(self):
        """Start showing typing indicator"""
        if self.is_active:
            return
        
        self.is_active = True
        self.stop_event.clear()
        self.placeholder = self.container.empty()
        
        self.thread = threading.Thread(target=self._show_indicator, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop showing typing indicator"""
        if self.is_active:
            self.stop_event.set()
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=1.0)
            self.is_active = False
            if self.placeholder:
                self.placeholder.empty()
    
    def _show_indicator(self):
        """Show animated typing indicator"""
        dots = 0
        while not self.stop_event.is_set():
            try:
                indicator = self.message + "." * (dots % 4)
                self.placeholder.markdown(f"🤖 **Assistant:** {indicator}")
                dots += 1
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"❌ Typing indicator error: {e}")
                break

class ProgressTracker:
    """Tracks and displays progress for long operations"""
    
    def __init__(self, container, total_steps: int = 100):
        self.container = container
        self.total_steps = total_steps
        self.current_step = 0
        self.progress_bar = None
        self.status_text = None
        self.is_active = False
    
    def start(self, title: str = "Processing..."):
        """Start progress tracking"""
        self.is_active = True
        self.current_step = 0
        
        self.status_text = self.container.empty()
        self.progress_bar = st.progress(0)
        
        self.status_text.text(title)
    
    def update(self, step: int, status: str = None):
        """Update progress"""
        if not self.is_active:
            return
        
        self.current_step = min(step, self.total_steps)
        progress = self.current_step / self.total_steps
        
        self.progress_bar.progress(progress)
        
        if status:
            self.status_text.text(status)
    
    def complete(self, message: str = "Complete!"):
        """Mark progress as complete"""
        if self.is_active:
            self.progress_bar.progress(1.0)
            self.status_text.text(message)
            self.is_active = False
    
    def stop(self):
        """Stop progress tracking"""
        self.is_active = False
        if self.progress_bar:
            self.progress_bar.empty()
        if self.status_text:
            self.status_text.empty()

def stream_response(response: str, container=None, chunk_size: int = 50, delay: float = 0.05) -> ResponseStreamer:
    """Convenience function to stream a response"""
    if container is None:
        container = st.container()
    
    streamer = ResponseStreamer(container, chunk_size, delay)
    streamer.start_streaming(response)
    return streamer

def show_typing_indicator(container=None, message: str = "Thinking...") -> TypingIndicator:
    """Convenience function to show typing indicator"""
    if container is None:
        container = st.container()
    
    indicator = TypingIndicator(container, message)
    indicator.start()
    return indicator

def track_progress(container=None, total_steps: int = 100, title: str = "Processing...") -> ProgressTracker:
    """Convenience function to track progress"""
    if container is None:
        container = st.container()
    
    tracker = ProgressTracker(container, total_steps)
    tracker.start(title)
    return tracker

# Performance monitoring for streaming
class StreamingMetrics:
    """Tracks streaming performance metrics"""
    
    def __init__(self):
        self.metrics = {
            'total_streams': 0,
            'total_chars_streamed': 0,
            'avg_stream_time': 0,
            'avg_chars_per_second': 0,
            'stream_errors': 0
        }
        self.current_streams = {}
    
    def start_stream(self, stream_id: str, total_chars: int):
        """Start tracking a stream"""
        self.current_streams[stream_id] = {
            'start_time': time.time(),
            'total_chars': total_chars,
            'chars_streamed': 0
        }
    
    def update_stream(self, stream_id: str, chars_streamed: int):
        """Update stream progress"""
        if stream_id in self.current_streams:
            self.current_streams[stream_id]['chars_streamed'] = chars_streamed
    
    def end_stream(self, stream_id: str, success: bool = True):
        """End tracking a stream"""
        if stream_id not in self.current_streams:
            return
        
        stream_data = self.current_streams.pop(stream_id)
        stream_time = time.time() - stream_data['start_time']
        
        if success:
            self.metrics['total_streams'] += 1
            self.metrics['total_chars_streamed'] += stream_data['chars_streamed']
            
            # Update averages
            if self.metrics['total_streams'] > 0:
                self.metrics['avg_stream_time'] = (
                    (self.metrics['avg_stream_time'] * (self.metrics['total_streams'] - 1) + stream_time) 
                    / self.metrics['total_streams']
                )
                
                if stream_time > 0:
                    chars_per_second = stream_data['chars_streamed'] / stream_time
                    self.metrics['avg_chars_per_second'] = (
                        (self.metrics['avg_chars_per_second'] * (self.metrics['total_streams'] - 1) + chars_per_second)
                        / self.metrics['total_streams']
                    )
        else:
            self.metrics['stream_errors'] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get streaming metrics"""
        return self.metrics.copy()

# Global streaming metrics
streaming_metrics = StreamingMetrics()
