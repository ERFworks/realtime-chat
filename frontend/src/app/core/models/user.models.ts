export interface User {
  user_id: number;
  username: string;
  first_name: string;
  last_name: string | null;
  profile_pic: string | null;
}