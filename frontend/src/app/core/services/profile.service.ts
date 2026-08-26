import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { Profile, ProfileUpdate } from '../models/profile.models';

@Injectable({ providedIn: 'root' })
export class ProfileService {
  private readonly base = environment.apiBase;

  constructor(private http: HttpClient) {}

  getMe(): Observable<Profile> {
    return this.http.get<Profile>(`${this.base}/profile/me`);
  }

  updateProfile(payload: ProfileUpdate): Observable<Profile> {
    return this.http.patch<Profile>(`${this.base}/profile/me`, payload);
  }

  uploadAvatar(file: File): Observable<Profile> {
    const form = new FormData();
    form.append('file', file);

    return this.http.post<Profile>(
      `${this.base}/profile/me/picture`,
      form
    );
  }
}