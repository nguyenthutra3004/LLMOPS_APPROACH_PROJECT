import {
  customProvider,
  extractReasoningMiddleware,
  wrapLanguageModel,
} from 'ai';
import { xai } from '@ai-sdk/xai';
import { createOpenAI, openai } from '@ai-sdk/openai';
import { createOpenAICompatible } from '@ai-sdk/openai-compatible';

import { isTestEnvironment } from '../constants';
import {
  artifactModel,
  chatModel,
  reasoningModel,
  titleModel,
} from './models.test';

const qwen = createOpenAI({
  compatibility: 'strict',
  name: 'initial-sft',
  baseURL: 'https://production.quanghung20gg.site/v1',
  apiKey: 'm_a_ma',
});


const qwen3 = createOpenAI({
  compatibility: 'strict',
  name: 'thinking',
  baseURL: 'https://thinking.quanghung20gg.site/v1',
  apiKey: 'm_a_ma',
});

export const myProvider = isTestEnvironment
  ? customProvider({
      languageModels: {
        'chat-model': chatModel,
        'chat-model-reasoning': reasoningModel,
        'title-model': titleModel,
        'artifact-model': artifactModel,
      },
    })
  : customProvider({
      languageModels: {
        'chat-model': qwen('initial-sft'),
        'chat-model-reasoning': wrapLanguageModel({
          model: qwen3('thinking'),
          middleware: extractReasoningMiddleware({ tagName: 'think' }),
        }),
        'title-model': qwen('initial-sft'),
        'artifact-model': qwen('initial-sft'),
      },
    });
