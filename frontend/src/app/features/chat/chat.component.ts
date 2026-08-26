import {
  Component,
  ElementRef,
  OnDestroy,
  OnInit,
  ViewChild,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import {
  BehaviorSubject,
  Subject,
  Subscription,
  debounceTime,
  distinctUntilChanged,
  finalize,
  switchMap,
  of,
} from 'rxjs';

import { ChatService } from '../../core/services/chat.service';
import { ProfileService } from '../../core/services/profile.service';
import { UserService } from '../../core/services/user.service';
import { FriendService } from '../../core/services/friend.service';
import { LoginService } from '../../core/services/login.service';

import {
  Conversation,
  Message,
  Participant,
  WsIncoming,
} from '../../core/models/chat.model';

import { Profile } from '../../core/models/profile.models';
import { User } from '../../core/models/user.models';
import { Friend, FriendRequest } from '../../core/models/friend.models';

type Tab = 'chats' | 'contacts' | 'requests';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat.component.html',
  styleUrl: './chat.component.scss',
})
export class ChatComponent implements OnInit, OnDestroy {
  readonly tab = signal<Tab>('chats');
  search = '';

  readonly me = signal<User | undefined>(undefined);
  readonly myProfile = signal<Profile | undefined>(undefined);

  readonly conversations = signal<Conversation[]>([]);
  readonly loadingConversations = signal(true);

  readonly friends = signal<Friend[]>([]);
  readonly loadingFriends = signal(true);

  readonly pendingRequests = signal<FriendRequest[]>([]);
  readonly loadingRequests = signal(false);
  readonly requestsLoaded = signal(false);
  readonly requestsLoadError = signal(false);
  readonly respondingToId = signal<number | null>(null);

  readonly activeConversation = signal<Conversation | undefined>(undefined);

  readonly messages$ = new BehaviorSubject<Message[]>([]);
  readonly loadingMessages$ = new BehaviorSubject(false);
  readonly messagesError$ = new BehaviorSubject('');

  @ViewChild('messagesEl') private messagesEl?: ElementRef<HTMLElement>;

  draft = '';

  showProfile = false;

  readonly savingProfile$ = new BehaviorSubject(false);
  readonly uploadingAvatar$ = new BehaviorSubject(false);
  readonly profileError$ = new BehaviorSubject('');
  readonly profileSuccess$ = new BehaviorSubject('');

  profileBio = '';

  showSearch = false;

  readonly searchQuery$ = new BehaviorSubject('');
  readonly searchResults$ = new BehaviorSubject<User[]>([]);
  readonly searching$ = new BehaviorSubject(false);

  readonly sentRequests = signal(new Set<number>());
  readonly sendingTo = signal<number | null>(null);
  readonly searchError = signal('');

  readonly toast$ = new BehaviorSubject('');

  private readonly searchTrigger$ = new Subject<string>();
  private toastTimer?: ReturnType<typeof setTimeout>;
  private subs: Subscription[] = [];
  private requestsLoadInFlight = false;

  constructor(
    private chat: ChatService,
    private profile: ProfileService,
    private user: UserService,
    private friend: FriendService,
    private login: LoginService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.chat.connect();

    this.subs.push(
      this.chat.incoming$.subscribe((msg) => this.handleWs(msg))
    );

    this.user.getMe().subscribe({
      next: (u) => this.me.set(u),
      error: () => {},
    });

    this.profile.getMe().subscribe({
      next: (p) => {
        this.myProfile.set(p);
        this.profileBio = p.biography || '';
      },
      error: () => {},
    });

    // All initial data is fetched once on entry; switchTab() only changes the tab.
    this.loadInitialData();

    this.subs.push(
      this.searchTrigger$
        .pipe(
          debounceTime(300),
          distinctUntilChanged(),
          switchMap((q) => {
            const trimmed = q.trim();

            if (!trimmed) {
              this.searching$.next(false);
              this.searchResults$.next([]);
              return of([]);
            }

            this.searching$.next(true);

            return this.user.search(trimmed);
          })
        )
        .subscribe({
          next: (users) => {
            const friendIds = new Set(
              this.friends().map((f) => f.user_id)
            );

            this.searchResults$.next(
              users.filter(
                (u) =>
                  u.user_id !== this.me()?.user_id &&
                  !friendIds.has(u.user_id) &&
                  !this.sentRequests().has(u.user_id)
              )
            );

            this.searching$.next(false);
          },
          error: () => {
            this.searchResults$.next([]);
            this.searching$.next(false);
          },
        })
    );
  }

  private loadInitialData(): void {
    this.loadConversations();
    this.loadFriends();
    this.loadRequests();
  }

  otherParticipant(
    conversation: Conversation
  ): Participant | undefined {
    const me = this.me();

    if (!me) return undefined;

    return conversation.participants.find(
      (p) => p.user_id !== me.user_id
    );
  }

  displayName(
    conversation: Conversation
  ): string {
    const other = this.otherParticipant(conversation);

    return (
      other?.first_name ||
      other?.username ||
      `Conversation ${conversation.conversation_id}`
    );
  }

  displayAvatar(
    conversation: Conversation
  ): string | undefined {
    return this.otherParticipant(conversation)?.profile_pic || undefined;
  }

  displayInitial(
    conversation: Conversation
  ): string {
    return this.displayName(conversation)[0] || '?';
  }

  loadConversations(): void {
    this.loadingConversations.set(true);

    this.chat.getConversations().subscribe({
      next: (conversations) => {
        this.conversations.set(
          [...conversations].sort(
            (a, b) =>
              new Date(b.updated_at).getTime() -
              new Date(a.updated_at).getTime()
          )
        );

        this.loadingConversations.set(false);
      },
      error: () => {
        this.loadingConversations.set(false);
      },
    });
  }

  loadFriends(): void {
    this.loadingFriends.set(true);

    this.friend.getFriends().subscribe({
      next: (friends) => {
        this.friends.set(friends);
        this.loadingFriends.set(false);
      },
      error: () => {
        this.friends.set([]);
        this.loadingFriends.set(false);
      },
    });
  }

  refreshFriends(): void {
    this.loadFriends();
  }

  get filteredConversations(): Conversation[] {
    const q = this.search.trim().toLowerCase();

    if (!q) return this.conversations();

    return this.conversations().filter((c) =>
      this.displayName(c).toLowerCase().includes(q)
    );
  }

  get filteredFriends(): Friend[] {
    const q = this.search.trim().toLowerCase();

    if (!q) return this.friends();

    return this.friends().filter((f) =>
      `${f.username} ${f.first_name ?? ''} ${f.last_name ?? ''}`
        .toLowerCase()
        .includes(q)
    );
  }

  selectConversation(
    conversation: Conversation
  ): void {
    const convId = conversation?.conversation_id;

    if (!convId) {
      this.messagesError$.next('Invalid conversation');
      return;
    }

    this.activeConversation.set(conversation);
    this.messages$.next([]);
    this.messagesError$.next('');
    this.loadingMessages$.next(true);

    this.chat.getMessages(convId).subscribe({
      next: (messages) => {
        this.messages$.next(
          [...messages].sort(
            (a, b) =>
              new Date(a.created_at).getTime() -
              new Date(b.created_at).getTime()
          )
        );

        this.loadingMessages$.next(false);
        this.scrollToBottom();
      },
      error: () => {
        this.messagesError$.next('Failed to load messages');
        this.loadingMessages$.next(false);
      },
    });
  }

  startChatWith(friend: Friend): void {
    const existing = this.conversations().find((c) => {
      const other = this.otherParticipant(c);

      return other?.user_id === friend.user_id;
    });

    if (existing) {
      this.selectConversation(existing);
      this.tab.set('chats');
      return;
    }

    this.chat.createConversation(friend.user_id).subscribe({
      next: (conv) => {
        this.conversations.set([
          conv,
          ...this.conversations(),
        ]);

        this.selectConversation(conv);
        this.tab.set('chats');
      },
      error: (err) => {
        this.showToast(
          err?.error?.detail ||
          'Could not start chat'
        );
      },
    });
  }

  switchTab(tab: Tab): void {
    this.tab.set(tab);
  }

  loadRequests(): void {
    if (this.requestsLoadInFlight) return;

    this.requestsLoadInFlight = true;
    this.loadingRequests.set(true);
    this.requestsLoadError.set(false);

    this.friend
      .getRequests()
      .pipe(
        finalize(() => {
          this.requestsLoadInFlight = false;
          this.loadingRequests.set(false);
          this.requestsLoaded.set(true);
        })
      )
      .subscribe({
        next: (requests) => {
          this.pendingRequests.set(
            requests.filter(
              (r) => r.status === 'pending'
            )
          );
        },
        error: (err) => {
          this.pendingRequests.set([]);
          this.requestsLoadError.set(true);

          this.showToast(
            err?.error?.detail ||
            'Failed to load requests'
          );
        },
      });
  }

  get pendingCount(): number {
    return this.pendingRequests().length;
  }

  acceptRequest(
    request: FriendRequest
  ): void {
    this.respondingToId.set(
      request.friendship_id
    );

    this.friend
      .acceptRequest(request.friendship_id)
      .subscribe({
        next: () => {
          this.pendingRequests.set(
            this.pendingRequests().filter(
              (r) =>
                r.friendship_id !==
                request.friendship_id
            )
          );

          this.respondingToId.set(null);

          this.refreshFriends();
          this.loadConversations();

          this.showToast(
            'You are now friends'
          );

          this.startChatWith(
            request.requester
          );
        },
        error: (err) => {
          this.respondingToId.set(null);

          this.showToast(
            err?.error?.detail ||
            'Failed to accept request'
          );
        },
      });
  }

  rejectRequest(
    request: FriendRequest
  ): void {
    this.respondingToId.set(
      request.friendship_id
    );

    this.friend
      .rejectRequest(request.friendship_id)
      .subscribe({
        next: () => {
          this.pendingRequests.set(
            this.pendingRequests().filter(
              (r) =>
                r.friendship_id !==
                request.friendship_id
            )
          );

          this.respondingToId.set(null);

          this.showToast(
            'Request rejected'
          );
        },
        error: (err) => {
          this.respondingToId.set(null);

          this.showToast(
            err?.error?.detail ||
            'Failed to reject request'
          );
        },
      });
  }

  openSearch(): void {
    this.showSearch = true;
    this.searchQuery$.next('');
    this.searchResults$.next([]);
    this.searchError.set('');
  }

  closeSearch(): void {
    this.showSearch = false;
    this.searchError.set('');
  }

  onSearchInput(
    value: string
  ): void {
    this.searchQuery$.next(value);
    this.searchTrigger$.next(value);
  }

  sendFriendRequest(
    userId: number
  ): void {
    this.sendingTo.set(userId);
    this.searchError.set('');

    this.friend.sendRequest(userId).subscribe({
      next: () => {
        this.sentRequests.update(
          (sent) => new Set(sent).add(userId)
        );
        this.sendingTo.set(null);

        const current =
          this.searchResults$.value;

        this.searchResults$.next(
          current.filter(
            (u) => u.user_id !== userId
          )
        );

        this.loadRequests();

        this.showToast(
          'Friend request sent'
        );
      },
      error: (err) => {
        this.sendingTo.set(null);

        this.searchError.set(
          err?.error?.detail ||
          'Failed to send request'
        );
      },
    });
  }

  send(): void {
    const body = this.draft.trim();
    const active = this.activeConversation();

    if (
      !body ||
      !active
    ) {
      return;
    }

    this.chat.sendMessage(
      active.conversation_id,
      body
    );

    this.draft = '';
  }

  isMine(
    message: Message
  ): boolean {
    const me = this.me();

    return !!me &&
      message.sender_id ===
      me.user_id;
  }

  private scrollToBottom(): void {
    setTimeout(() => {
      const el =
        this.messagesEl?.nativeElement;

      if (el) {
        el.scrollTop =
          el.scrollHeight;
      }
    }, 0);
  }

  private handleWs(
    message: WsIncoming
  ): void {
    if (
      message.type === 'message' &&
      message.data
    ) {
      const newMessage =
        message.data as Message;

      const idx =
        this.conversations().findIndex(
          (c) =>
            c.conversation_id ===
            newMessage.conversation_id
        );

      if (idx !== -1) {
        const updated = {
          ...this.conversations()[idx],
          updated_at:
            newMessage.created_at,
        };

        this.conversations.set([
          updated,
          ...this.conversations().slice(0, idx),
          ...this.conversations().slice(idx + 1),
        ]);
      }

      const active = this.activeConversation();

      if (
        active &&
        newMessage.conversation_id ===
        active.conversation_id
      ) {
        const current =
          this.messages$.value;

        if (
          current.some(
            (message) =>
              message.message_id ===
              newMessage.message_id
          )
        ) {
          return;
        }

        this.messages$.next([
          ...current,
          newMessage,
        ]);

        this.scrollToBottom();
      }
    }

    if (
      message.type === 'friend_accepted' &&
      message.data
    ) {
      this.refreshFriends();
      this.loadConversations();
      this.loadRequests();
    }
  }

  openProfile(): void {
    this.showProfile = true;
    this.profileError$.next('');
    this.profileSuccess$.next('');

    const profile = this.myProfile();

    if (profile) {
      this.profileBio =
        profile.biography || '';
    }
  }

  closeProfile(): void {
    this.showProfile = false;
    this.profileError$.next('');
    this.profileSuccess$.next('');
  }

  saveProfile(): void {
    this.savingProfile$.next(true);
    this.profileError$.next('');
    this.profileSuccess$.next('');

    this.profile
      .updateProfile({
        biography:
          this.profileBio || null,
      })
      .subscribe({
        next: (profile) => {
          this.myProfile.set(profile);
          this.profileBio =
            profile.biography || '';

          this.savingProfile$.next(false);

          this.profileSuccess$.next(
            'Profile saved!'
          );

          setTimeout(
            () =>
              this.profileSuccess$.next(''),
            3000
          );
        },
        error: () => {
          this.savingProfile$.next(false);

          this.profileError$.next(
            'Failed to save profile'
          );
        },
      });
  }

  onAvatarSelected(
    event: Event
  ): void {
    const input =
      event.target as HTMLInputElement;

    const file =
      input.files?.[0];

    if (!file) return;

    this.uploadingAvatar$.next(true);
    this.profileError$.next('');
    this.profileSuccess$.next('');

    this.profile
      .uploadAvatar(file)
      .subscribe({
        next: (profile) => {
          this.myProfile.set(profile);

          const me = this.me();

          if (me) {
            this.me.set({
              ...me,
              profile_pic:
                profile.profile_pic,
            });
          }

          this.uploadingAvatar$.next(false);

          this.profileSuccess$.next(
            'Photo updated!'
          );

          setTimeout(
            () =>
              this.profileSuccess$.next(''),
            3000
          );
        },
        error: () => {
          this.uploadingAvatar$.next(false);

          this.profileError$.next(
            'Failed to upload photo'
          );
        },
      });
  }

  private showToast(
    msg: string
  ): void {
    this.toast$.next(msg);

    if (this.toastTimer) {
      clearTimeout(this.toastTimer);
    }

    this.toastTimer =
      setTimeout(
        () => this.toast$.next(''),
        3000
      );
  }

  logout(): void {
    this.chat.disconnect();
    this.login.logout();
    this.router.navigate(['/login']);
  }

  ngOnDestroy(): void {
    this.subs.forEach(
      (s) => s.unsubscribe()
    );

    if (this.toastTimer) {
      clearTimeout(this.toastTimer);
    }

    this.chat.disconnect();
  }
}
