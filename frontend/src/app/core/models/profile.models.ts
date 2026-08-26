export interface Profile {
  profile_id: number;
  user_id: number;
  biography: string | null;
  profile_pic: string | null;
}

export interface ProfileUpdate {
  biography: string | null;
}