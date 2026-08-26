import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { catchError, finalize, of, switchMap } from 'rxjs';

import { LoginService } from '../../core/services/login.service';
import { UserService } from '../../core/services/user.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss',
})
export class LoginComponent {
  isRegister = false;
  loadingLogin = false;
  loadingRegister = false;
  error = '';

  loginData = { username: '', password: '' };

  registerData = {
    username: '',
    first_name: '',
    last_name: '',
    password: '',
  };

  constructor(
    private loginService: LoginService,
    private userService: UserService,
    private router: Router
  ) {}

  toggle(register: boolean): void {
    this.isRegister = register;
    this.error = '';
  }

  onLogin(): void {
    if (!this.loginData.username || !this.loginData.password) {
      this.error = 'Username and password are required';
      return;
    }

    this.loadingLogin = true;
    this.error = '';

    this.loginService
      .login(this.loginData)
      .pipe(finalize(() => (this.loadingLogin = false)))
      .subscribe({
        next: () => {
          this.userService.getMe().subscribe();
          this.router.navigate(['/chat']);
        },
        error: (err) => {
          this.error = err?.error?.detail || 'Login failed';
        },
      });
  }

  onRegister(): void {
    const { username, first_name, last_name, password } = this.registerData;

    if (!username || !first_name || !password) {
      this.error = 'Please fill in all required fields';
      return;
    }

    if (password.length < 8) {
      this.error = 'Password must be at least 8 characters';
      return;
    }

    this.loadingRegister = true;
    this.error = '';

    const payload = {
      username,
      first_name,
      last_name: last_name || undefined,
      password,
    };

    this.loginService
      .register(payload)
      .pipe(
        catchError((err) => {
          const msg = err?.error?.detail || 'Registration failed';
          this.error = msg;
          return of(null);
        }),

        switchMap((result) => {
          if (result === null) {
            this.loadingRegister = false;
            return of(null);
          }

          return this.loginService.login({ username, password }).pipe(
            catchError(() => {
              this.isRegister = false;
              this.loadingRegister = false;
              this.error = 'Account created! Please log in.';
              return of(null);
            }),

            switchMap((loginResult) => {
              if (!loginResult) {
                return of(null);
              }

              return this.userService.getMe().pipe(
                catchError(() => of(null))
              );
            })
          );
        }),

        finalize(() => {
          if (this.loadingRegister) {
            this.loadingRegister = false;
          }
        })
      )
      .subscribe((result) => {
        if (result !== null) {
          this.router.navigate(['/chat']);
        }
      });
  }

}