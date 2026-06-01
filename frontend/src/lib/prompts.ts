export interface Prompt {
  id: string
  title: string
  text: string
}

export interface PromptCategory {
  category: string
  prompts: Prompt[]
}

export const PROMPT_LIBRARY: PromptCategory[] = [
  {
    category: 'Adobe Analytics',
    prompts: [
      { id: 'aa-1', title: 'Create a segment', text: 'How do I create a segment in Adobe Analytics?' },
      { id: 'aa-2', title: 'Calculated metrics', text: 'How do I create a calculated metric in Adobe Analytics?' },
      { id: 'aa-3', title: 'Attribution IQ', text: 'What is Attribution IQ and how does it work in Adobe Analytics?' },
      { id: 'aa-4', title: 'Virtual report suites', text: 'What are virtual report suites and when should I use them?' },
      { id: 'aa-5', title: 'Marketing channels', text: 'How do I set up marketing channels in Adobe Analytics?' },
      { id: 'aa-6', title: 'Data warehouse', text: 'How does Data Warehouse work in Adobe Analytics?' },
      { id: 'aa-7', title: 'Fallout analysis', text: 'How does fallout analysis work in Analysis Workspace?' },
      { id: 'aa-8', title: 'eVars and props limits', text: 'What are the limits on eVars and props in Adobe Analytics?' },
    ],
  },
  {
    category: 'Customer Journey Analytics',
    prompts: [
      { id: 'cja-1', title: 'What is a Connection', text: 'What is a Connection in Customer Journey Analytics?' },
      { id: 'cja-2', title: 'Create a Data View', text: 'How do I create a Data View in CJA?' },
      { id: 'cja-3', title: 'Derived fields', text: 'What are derived fields in CJA and how are they different from calculated metrics?' },
      { id: 'cja-4', title: 'Filters vs segments', text: 'How are filters in CJA different from segments in Adobe Analytics?' },
      { id: 'cja-5', title: 'Cross-channel analysis', text: 'How does cross-channel analysis work in Customer Journey Analytics?' },
      { id: 'cja-6', title: 'Data View vs VRS', text: 'When should I use a Data View vs a Virtual Report Suite?' },
    ],
  },
  {
    category: 'Adobe Experience Platform',
    prompts: [
      { id: 'aep-1', title: 'XDM schema', text: 'What is XDM schema and how does schema composition work in AEP?' },
      { id: 'aep-2', title: 'Real-Time CDP', text: 'What is Real-Time CDP and how does it differ from AEP?' },
      { id: 'aep-3', title: 'Identity resolution', text: 'How does identity resolution work in Adobe Experience Platform?' },
      { id: 'aep-4', title: 'Audience segmentation', text: 'How do I create an audience segment in AEP?' },
      { id: 'aep-5', title: 'Data ingestion', text: 'What are the different ways to ingest data into Adobe Experience Platform?' },
      { id: 'aep-6', title: 'Real-Time Profile', text: 'What is the Real-Time Customer Profile in AEP?' },
    ],
  },
  {
    category: 'Comparisons',
    prompts: [
      { id: 'cmp-1', title: 'AA vs CJA', text: 'What is the difference between Adobe Analytics and Customer Journey Analytics?' },
      { id: 'cmp-2', title: 'Migrate AA to CJA', text: 'How do I migrate from Adobe Analytics to Customer Journey Analytics?' },
      { id: 'cmp-3', title: 'Metric vs calculated metric', text: 'What is the difference between a metric and a calculated metric?' },
    ],
  },
]
