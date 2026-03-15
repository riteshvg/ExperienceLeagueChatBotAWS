# Branch Strategy

This repository uses a three-branch strategy for development and deployment:

## 🌿 **Main Branch**
- **Purpose**: Production-ready, stable code
- **Deployment**: Automatically deployed to Railway
- **Status**: ✅ Currently stable with streaming responses
- **Features**: Complete Adobe Analytics AI Assistant with real-time chat

## 🔧 **Development Branch**
- **Purpose**: Integration and testing of new features
- **Usage**: Merge feature branches here before main
- **Testing**: Full integration testing before production
- **Status**: Ready for development work

## 🚀 **Enhancements Branch**
- **Purpose**: Active development of new features and improvements
- **Usage**: Current working branch for new development
- **Features**: Experimental features, UI improvements, new capabilities
- **Status**: ✅ Currently active for further development

## 📋 **Development Workflow**

1. **Create feature branch** from `enhancements`
2. **Develop and test** new features
3. **Merge to development** for integration testing
4. **Merge to main** when ready for production

## 🎯 **Current Status**

- **Main**: Production-ready with streaming responses
- **Development**: Ready for integration testing
- **Enhancements**: ✅ Active development branch

## 🔄 **Branch Management**

```bash
# Switch to enhancements for development
git checkout enhancements

# Create new feature branch
git checkout -b feature/new-feature

# Merge back to enhancements
git checkout enhancements
git merge feature/new-feature

# Push changes
git push origin enhancements
```

## 📝 **Next Steps**

Continue development on the `enhancements` branch for:
- New features
- UI improvements
- Performance optimizations
- Additional integrations
