import type { ChangeEvent } from 'react';
import React, { useState } from 'react';

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
        placeholder="trajektorien filtern"
        value={filter}
        onChange={handleChange}
        className="mt-3 h-10 w-full rounded-xl bg-gray-50 p-4 ps-4 text-lg font-extralight shadow-md"
      />
    </div>
  );
};

export default SearchFilter;
