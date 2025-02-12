import React from 'react';

import ROSBAGProcessorForm from '@/src/app/hochladen/components/rosbagProcessorForm';

import CSVUploadForm from './components/CSVUploadForm';

const Hochladen: React.FC = () => {
  return (
    <div className="flex h-fullscreen justify-center overflow-scroll">
      <CSVUploadForm />
      <ROSBAGProcessorForm />
    </div>
  );
};

export default Hochladen;
