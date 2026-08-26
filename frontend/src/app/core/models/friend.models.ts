export interface Friend {
  user_id: number;
  username: string;
  first_name: string;
  last_name: string | null;
  profile_pic: string | null;
}

export interface FriendRequest {
  friendship_id: number;
  requester_id: number;
  addressee_id: number;
  status: 'pending' | 'accepted' | 'rejected';
  created_at: string;
  requester: {
    user_id: number;
    username: string;
    first_name: string;
    last_name: string | null;
    profile_pic: string | null;
  };
}