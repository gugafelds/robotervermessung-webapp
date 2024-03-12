'use client';

import type { ReactNode } from 'react';
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from 'react';

import type { GenericEvent } from '@/types/events';

export type ModalsState<T> = {
  modalData: T | undefined;
  isOpen: boolean;
  handleOpenSlideOver: (modalData: T) => (e: GenericEvent) => void;
  handleClearModalData: () => void;
  handleCloseSlideOver: () => void;
};

const ModalContext = createContext<ModalsState<any>>({} as ModalsState<any>);

type ModalProviderProps = {
  children: ReactNode;
};

export const ModalsProvider = <T extends unknown>({
  children,
}: ModalProviderProps) => {
  const [isOpen, setOpen] = useState<boolean>(false);
  const [modalData, setModalData] = useState<T>();

  const handleOpenSlideOver = useCallback(
    (data: T) => (e: GenericEvent) => {
      e.stopPropagation();
      setModalData(data);
      setOpen(true);
    },
    [],
  );

  const handleClearModalData = () => {
    setModalData(undefined);
  };

  const handleCloseSlideOver = () => {
    setOpen(false);
  };

  const contextValue = useMemo(
    () => ({
      modalData,
      isOpen,
      handleOpenSlideOver,
      handleCloseSlideOver,
      handleClearModalData,
    }),
    [handleOpenSlideOver, isOpen, modalData],
  );

  return (
    <ModalContext.Provider value={contextValue}>
      {children}
    </ModalContext.Provider>
  );
};

export const useModals = <T extends unknown>(): ModalsState<T> =>
  useContext(ModalContext);
