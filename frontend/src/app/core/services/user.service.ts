import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { User } from '../models/user.models';

@Injectable({
  providedIn: 'root',
})
export class UserService {
  private readonly base = environment.apiBase;

  constructor(private http: HttpClient) {}

  getMe(): Observable<User> {
    return this.http.get<User>(`${this.base}/auth/me`);
  }

  search(query: string): Observable<User[]> {
    const params = new HttpParams().set('q', query);

    return this.http.get<User[]>(
      `${this.base}/users/search`,
      { params }
    );
  }
}