import { ContactCard } from './components/ContactCard';
import { ProjectInfo } from './components/ProjectInfo';

export default async function Home() {
  return (
    <section className='flex flex-col xl:flex-row'>
      <ProjectInfo />
      <ContactCard />
    </section>
  );
}
