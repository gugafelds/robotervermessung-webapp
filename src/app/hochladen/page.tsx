import React from 'react';

import CSVUploadForm from './components/CSVUploadForm';

const Hochladen: React.FC = () => {
  return (
    <div className="flex h-fullscreen justify-center overflow-y-auto">
      <CSVUploadForm />
    </div>
  );
};

export default Hochladen;
