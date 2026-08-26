import { Routes } from '@angular/router';
import { loginGuard } from './core/guards/login.guard';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'chat',
  },
  {
    path: 'login',
    loadComponent: () =>
      import('./features/login/login.component').then(
        (m) => m.LoginComponent
      ),
  },
  {
    path: 'chat',
    canActivate: [loginGuard],
    loadComponent: () =>
      import('./features/chat/chat.component').then(
        (m) => m.ChatComponent
      ),
  },
  {
    path: '**',
    redirectTo: 'chat',
  },
];