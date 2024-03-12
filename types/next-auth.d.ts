import type { ObjectId } from 'mongodb';

import type { UserObject } from '@/types/main';

declare module 'next-auth' {
  interface User {
    _id: ObjectId | undefined;
    username: string;
    email: string;
    password: string;
  }

  interface Session {
    user: UserObject;
    expires: string;
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    uid: UserObject;
  }
}
