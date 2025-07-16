export const DEFAULT_CHAT_MODEL: string = 'chat-model';

export interface ChatModel {
  id: string;
  name: string;
  description: string;
}

export const chatModels: Array<ChatModel> = [
  {
    id: 'chat-model',
    name: 'Trò chuyện',
    description: 'Mô hình trò chuyện thông thường',
  },
  {
    id: 'chat-model-reasoning',
    name: 'Suy luận',
    description: 'Mô hình có khả năng suy luận',
  },
];
