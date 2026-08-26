import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, switchMap, throwError } from 'rxjs';

import { LoginService } from '../services/login.service';

export const loginInterceptor: HttpInterceptorFn = (req, next) => {
  const loginService = inject(LoginService);
  const router = inject(Router);
  const isAuthEndpoint = /\/auth\/(login|register|refresh|logout)$/.test(req.url);
  const token = loginService.getToken();
  const authReq = token && !isAuthEndpoint
    ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : req;

  return next(authReq).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status !== 401 || isAuthEndpoint || !loginService.getRefreshToken()) {
        if (error.status === 401 && !isAuthEndpoint) {
          loginService.logout();
          void router.navigate(['/login']);
        }
        return throwError(() => error);
      }

      return loginService.refresh().pipe(
        switchMap((tokens) =>
          next(req.clone({
            setHeaders: { Authorization: `Bearer ${tokens.access_token}` },
          }))
        ),
        catchError((refreshError) => {
          loginService.logout();
          void router.navigate(['/login']);
          return throwError(() => refreshError);
        })
      );
    })
  );
};
