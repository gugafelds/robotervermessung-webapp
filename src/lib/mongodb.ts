// eslint-disable-next-line import/no-extraneous-dependencies
import type { Db } from 'mongodb';
import { MongoClient } from 'mongodb';

export async function getMongoClient(): Promise<MongoClient> {
  /**
   * Global is used here to maintain a cached connection across hot reloads
   * in development. This prevents connections growing exponentiatlly
   * during API Route usage.
   * https://github.com/vercel/next.js/pull/17666
   */
  if (!(global as any).mongoClientPromise) {
    const client = new MongoClient(
      process.env.MONGODB_URI ||
        'mongodb+srv://umbertobarros:8Cmgpiv53SaYEp7k@cluster0.su3gj7l.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0',
    );
    // client.connect() returns an instance of MongoClient when resolved
    (global as any).mongoClientPromise = client.connect();
    // eslint-disable-next-line @typescript-eslint/no-shadow
  }
  return (global as any).mongoClientPromise;
}

export async function getMongoDb(): Promise<Db> {
  const mongoClient = await getMongoClient();
  return mongoClient.db('robotervermessung');
}
