import type { ChangeEvent} from 'react';
import { useState } from 'react';

type SearchFilterProps = {
  onFilterChange: (filter: string) => void;
};

const SearchFilter: React.FC<SearchFilterProps> = ({ onFilterChange }) => {
  const [filter, setFilter] = useState<string>('');

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    const { value } = event.target;
    setFilter(value);
    onFilterChange(value);
  };

  return (
    <div>
      <input
        type="text"
        placeholder="  filter trajectories"
        value={filter}
        onChange={handleChange}
      />
    </div>
  );
};

export default SearchFilter;