import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import {
  Observable,
  Subject,
} from 'rxjs';

import { environment } from '../../../environments/environment';
import { LoginService } from './login.service';

import {
  Conversation,
  Message,
  WsIncoming,
  WsOutgoing,
} from '../models/chat.model';

@Injectable({
  providedIn: 'root',
})
export class ChatService {
  private ws?: WebSocket;
  private manualClose = false;

  readonly incoming$ = new Subject<WsIncoming>();
  readonly errors$ = new Subject<string>();
  readonly status$ = new Subject<'connecting' | 'open' | 'closed'>();
  private reconnectTimer?: ReturnType<typeof setTimeout>;

  constructor(
    private http: HttpClient,
    private login: LoginService
  ) {}

  getConversations(): Observable<Conversation[]> {
    return this.http.get<Conversation[]>(
      `${environment.apiBase}/conversations`
    );
  }

  createConversation(otherUserId: number): Observable<Conversation> {
    return this.http.post<Conversation>(
      `${environment.apiBase}/conversations`,
      { other_user_id: otherUserId }
    );
  }

  getMessages(
    conversationId: number
  ): Observable<Message[]> {
    return this.http.get<Message[]>(
      `${environment.apiBase}/conversations/${conversationId}/messages`
    );
  }

  connect(): void {
    if (
      this.ws &&
      (
        this.ws.readyState === WebSocket.OPEN ||
        this.ws.readyState === WebSocket.CONNECTING
      )
    ) {
      return;
    }

    const token = this.login.getToken();

    if (!token) {
      return;
    }

    this.manualClose = false;
    this.status$.next('connecting');

    this.ws = new WebSocket(
      `${environment.wsBase}/ws?token=${encodeURIComponent(token)}`
    );

    this.ws.onopen = () => {
      this.status$.next('open');
    };

    this.ws.onmessage = (event: MessageEvent) => {
      let payload: WsIncoming;

      try {
        payload = JSON.parse(event.data);
      } catch {
        return;
      }

      if (payload.type === 'ping') {
        this.send({ type: 'pong' });
        return;
      }

      if (payload.type === 'error') {
        this.errors$.next(payload.detail ?? 'Unknown error');
        return;
      }

      this.incoming$.next(payload);
    };

    this.ws.onclose = () => {
      this.status$.next('closed');

      if (!this.manualClose && this.login.getToken()) {
        if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
        this.reconnectTimer = setTimeout(() => this.connect(), 3000);
      }
    };

    this.ws.onerror = () => {
      this.status$.next('closed');
    };
  }

  send(payload: WsOutgoing): void {
    if (
      this.ws &&
      this.ws.readyState === WebSocket.OPEN
    ) {
      this.ws.send(
        JSON.stringify(payload)
      );
    }
  }

  sendMessage(
    conversationId: number,
    body: string
  ): void {
    this.send({
      conversation_id: conversationId,
      body,
    });
  }

  disconnect(): void {
    this.manualClose = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = undefined;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = undefined;
    }
    this.status$.next('closed');
  }
}