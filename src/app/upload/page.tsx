import React from 'react';

import CSVUploadForm from './components/CSVUploadForm';

const Upload: React.FC = () => {
  return (
    <div className="flex h-fullscreen justify-center overflow-y-auto">
      <CSVUploadForm />
    </div>
  );
};

export default Upload;
