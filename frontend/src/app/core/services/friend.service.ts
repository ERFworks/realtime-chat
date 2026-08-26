import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import {
  Friend,
  FriendRequest,
} from '../models/friend.models';

@Injectable({
  providedIn: 'root',
})
export class FriendService {
  private readonly base = environment.apiBase;

  constructor(private http: HttpClient) {}

  getFriends(): Observable<Friend[]> {
    return this.http.get<Friend[]>(
      `${this.base}/friends`
    );
  }

  getRequests(): Observable<FriendRequest[]> {
    return this.http.get<FriendRequest[]>(
      `${this.base}/friends/requests`
    );
  }

  sendRequest(userId: number): Observable<Friend> {
    return this.http.post<Friend>(
      `${this.base}/friends/requests/${userId}`,
      {}
    );
  }

  acceptRequest(requestId: number): Observable<Friend> {
    return this.http.post<Friend>(
      `${this.base}/friends/requests/${requestId}/respond`,
      null,
      { params: { accept: 'true' } }
    );
  }

  rejectRequest(requestId: number): Observable<Friend> {
    return this.http.post<Friend>(
      `${this.base}/friends/requests/${requestId}/respond`,
      null,
      { params: { accept: 'false' } }
    );
  }
}