// useTimeout.ts
import { useState } from 'react';

interface TimeoutObject {
  id: string;
  timeout: NodeJS.Timeout;
}

export const useExecutionTimeout = (delay: number = 2000) => {
  const [timeouts, setTimeouts] = useState<TimeoutObject[]>([]);

  const clearTimeoutById = (id: string) => {
    let timeoutsCopy = [...timeouts];
    const timeoutObj = timeoutsCopy.find((timeout) => timeout.id === id);
    if (timeoutObj) {
      clearTimeout(timeoutObj.timeout);
      timeoutsCopy = timeoutsCopy.filter((timeout) => timeout.id !== id);
      setTimeouts(timeoutsCopy);
    }
  };

  const setExecutionTimeout = (id: string, callback: () => void) => {
    const timeout = setTimeout(() => {
      callback();
      clearTimeoutById(id);
    }, delay);

    setTimeouts([...timeouts, { id, timeout }]);
  };

  return { setExecutionTimeout, clearTimeoutById };
};
