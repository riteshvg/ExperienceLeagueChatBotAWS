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
    category: 'Adobe Target',
    prompts: [
      { id: 'at-1', title: 'Create an A/B test', text: 'How do I create an A/B test activity in Adobe Target?' },
      { id: 'at-2', title: 'A/B vs MVT', text: 'What is the difference between A/B testing and multivariate testing in Adobe Target?' },
      { id: 'at-3', title: 'Experience Targeting', text: 'How do I set up Experience Targeting (XT) activities in Adobe Target?' },
      { id: 'at-4', title: 'Recommendations', text: 'How do I set up a Recommendations activity in Adobe Target?' },
      { id: 'at-5', title: 'Auto-Target', text: 'What is Auto-Target in Adobe Target and how does it use machine learning?' },
      { id: 'at-6', title: 'Audiences', text: 'How do I create and manage audiences in Adobe Target?' },
      { id: 'at-7', title: 'Global mbox', text: 'What is the global mbox in Adobe Target and how do I configure it?' },
      { id: 'at-8', title: 'Reports & lift', text: 'How do I read the Lift and Confidence report for an A/B test in Adobe Target?' },
    ],
  },
  {
    category: 'Adobe Data Collection',
    prompts: [
      { id: 'dc-1', title: 'What is Tags/Launch', text: 'What is Adobe Tags (formerly Launch) and how does it work as a tag management system?' },
      { id: 'dc-2', title: 'Create a Tag rule', text: 'How do I create a rule in Adobe Tags to fire a custom event?' },
      { id: 'dc-3', title: 'Tags extensions', text: 'What are extensions in Adobe Tags and how do I install the Adobe Analytics extension?' },
      { id: 'dc-4', title: 'Publish a Tags library', text: 'What are the steps to build and publish a library in Adobe Tags?' },
      { id: 'dc-5', title: 'Tags environments', text: 'What is the difference between Development, Staging, and Production environments in Adobe Tags?' },
      { id: 'dc-6', title: 'What is Web SDK', text: 'What is the Adobe Experience Platform Web SDK (alloy.js) and why should I use it instead of AppMeasurement?' },
      { id: 'dc-7', title: 'sendEvent command', text: 'How do I use the sendEvent command in the Web SDK to send data to Adobe Analytics and AEP?' },
      { id: 'dc-8', title: 'Web SDK XDM mapping', text: 'How do I map my data to XDM schema when using the Experience Platform Web SDK?' },
      { id: 'dc-9', title: 'Web SDK vs AppMeasurement', text: 'What is the migration path from AppMeasurement to the Adobe Experience Platform Web SDK?' },
      { id: 'dc-10', title: 'Web SDK identity', text: 'How does identity management work in the Experience Platform Web SDK?' },
      { id: 'dc-11', title: 'What is a Datastream', text: 'What is a datastream in Adobe Experience Platform and how does it route data to different services?' },
      { id: 'dc-12', title: 'Configure a Datastream', text: 'How do I create and configure a datastream to send data to Adobe Analytics and AEP simultaneously?' },
      { id: 'dc-13', title: 'Datastream data prep', text: 'How does Data Prep for Data Collection work in a datastream?' },
      { id: 'dc-14', title: 'Override Datastream settings', text: 'How do I configure datastream overrides for per-environment settings?' },
      { id: 'dc-15', title: 'Edge Network overview', text: 'What is the Adobe Experience Platform Edge Network and how does it differ from the traditional data collection servers?' },
      { id: 'dc-16', title: 'Server API', text: 'What is the Edge Network Server API and when should I use it instead of the Web SDK?' },
      { id: 'dc-17', title: 'First-party data collection', text: 'How do I set up first-party data collection using the Edge Network?' },
      { id: 'dc-18', title: 'Mobile SDK vs Web SDK', text: 'How does the Adobe Experience Platform Mobile SDK compare to the Web SDK for data collection?' },
    ],
  },
  {
    category: 'Adobe Journey Optimizer',
    prompts: [
      { id: 'ajo-1', title: 'What is AJO', text: 'What is Adobe Journey Optimizer and how does it differ from Adobe Campaign?' },
      { id: 'ajo-2', title: 'Create a journey', text: 'How do I create a journey in Adobe Journey Optimizer?' },
      { id: 'ajo-3', title: 'Journey canvas', text: 'What are the different action and event nodes available in the Adobe Journey Optimizer journey canvas?' },
      { id: 'ajo-4', title: 'Decision management', text: 'What is decision management in Adobe Journey Optimizer and how do I set up an offer library?' },
      { id: 'ajo-5', title: 'Frequency capping', text: 'How do I configure frequency capping and suppression rules in Adobe Journey Optimizer?' },
      { id: 'ajo-6', title: 'AJO + AEP', text: 'How does Adobe Journey Optimizer use Adobe Experience Platform profiles and audiences to personalise journeys?' },
      { id: 'ajo-7', title: 'Email channel', text: 'How do I create and send an email message in Adobe Journey Optimizer?' },
      { id: 'ajo-8', title: 'Push notifications', text: 'How do I set up push notification campaigns in Adobe Journey Optimizer?' },
    ],
  },
  {
    category: 'Cross-Product',
    prompts: [
      { id: 'xp-1', title: 'AA vs CJA', text: 'What is the difference between Adobe Analytics and Customer Journey Analytics?' },
      { id: 'xp-2', title: 'Migrate AA → CJA', text: 'How do I migrate from Adobe Analytics to Customer Journey Analytics?' },
      { id: 'xp-3', title: 'AEP audiences in Target', text: 'How do I use Adobe Experience Platform audiences in Adobe Target for personalisation?' },
      { id: 'xp-4', title: 'Analytics → CJA data flow', text: 'How does data flow from Adobe Analytics into Customer Journey Analytics?' },
      { id: 'xp-5', title: 'Web SDK vs AppMeasurement', text: 'How do the Experience Platform Web SDK and AppMeasurement compare for sending data to Adobe Analytics and AEP?' },
      { id: 'xp-6', title: 'Real-Time CDP vs Analytics', text: 'What is the difference between Real-Time CDP and Adobe Analytics for audience building?' },
      { id: 'xp-7', title: 'Target + AEP integration', text: 'How do I integrate Adobe Target with Adobe Experience Platform for unified personalisation?' },
      { id: 'xp-8', title: 'Metric vs calculated metric', text: 'What is the difference between a metric and a calculated metric in Adobe Analytics and CJA?' },
    ],
  },
]
