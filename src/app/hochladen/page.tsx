import React from 'react';

import CSVUploadForm from './components/CSVUploadForm';

const Hochladen: React.FC = () => {
  return (
    <div className="flex h-fullscreen justify-center overflow-scroll">
      <CSVUploadForm />
    </div>
  );
};

export default Hochladen;
