export interface Participant {
  user_id: number;
  username: string;
  first_name: string;
  last_name: string | null;
  profile_pic: string | null;
}

export interface Conversation {
  conversation_id: number;
  conversation_type: 'private' | 'group';
  created_at: string;
  updated_at: string;
  participants: Participant[];
}

export interface Message {
  message_id: number;
  conversation_id: number;
  sender_id: number | null;
  body: string;
  created_at: string;
  edited_at: string | null;
  deleted_at: string | null;
}

export interface WsIncoming {
  type: string;
  data?: Message;
  detail?: string;
}

export interface WsOutgoing {
  type?: string;
  conversation_id?: number;
  body?: string;
}