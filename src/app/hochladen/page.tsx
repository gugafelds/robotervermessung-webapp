import React from 'react';

import ROSBAGProcessorForm from '@/src/app/hochladen/components/rosbagProcessorForm';

import CSVUploadForm from './components/CSVUploadForm';

const Hochladen: React.FC = () => {
  return (
    <div className="flex-row justify-center">
      <CSVUploadForm />
      <ROSBAGProcessorForm />
    </div>
  );
};

export default Hochladen;
