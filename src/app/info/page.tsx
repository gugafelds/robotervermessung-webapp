import { ContactCard } from './components/ContactCard';
import { ProjectInfo } from './components/ProjectInfo';

export default async function Home() {
  return (
    <main className="flex flex-row justify-center">
      <ProjectInfo />
      <ContactCard />
    </main>
  );
}
