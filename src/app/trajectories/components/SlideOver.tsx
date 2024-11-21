'use client';

import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon } from '@heroicons/react/20/solid';
import { Fragment, type ReactNode } from 'react';
import React from 'react';

import type {
  BahnPoseIst,
  BahnPoseTrans,
  BahnPositionSoll,
} from '@/types/main'; // Adjust import path as needed

import { Position3DPlot } from './Position3DPlot'; // Adjust import path as needed

type ModalProps = {
  title: string | ReactNode;
  open: boolean;
  onClose: () => void;
  children?: ReactNode;
  currentBahnPoseIst: BahnPoseIst[];
  currentBahnPoseTrans: BahnPoseTrans[];
  idealTrajectory: BahnPositionSoll[];
  isTransformed: boolean;
};

const SlideOver = ({
  title,
  open,
  onClose,
  children,
  currentBahnPoseTrans,
  currentBahnPoseIst,
  idealTrajectory,
  isTransformed,
}: ModalProps) => {
  return (
    <Transition.Root show={open} as={Fragment}>
      <Dialog as="div" className="relative z-10" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-in-out duration-500"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in-out duration-500"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-500/75 transition-opacity" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-hidden">
          <div className="absolute inset-0 overflow-hidden">
            <div className="pointer-events-none fixed inset-y-0 right-0 flex max-w-full pl-10">
              <Transition.Child
                as={Fragment}
                enter="transform transition ease-in-out duration-500 sm:duration-700"
                enterFrom="translate-x-full"
                enterTo="translate-x-0"
                leave="transform transition ease-in-out duration-500 sm:duration-700"
                leaveFrom="translate-x-0"
                leaveTo="translate-x-full"
              >
                <Dialog.Panel className="pointer-events-auto relative my-auto max-h-[90vh] w-screen max-w-xl">
                  {' '}
                  {/* Adjusted here */}
                  <Transition.Child
                    as={Fragment}
                    enter="ease-in-out duration-500"
                    enterFrom="opacity-0"
                    enterTo="opacity-100"
                    leave="ease-in-out duration-500"
                    leaveFrom="opacity-100"
                    leaveTo="opacity-0"
                  >
                    <div className="absolute left-0 top-0 -ml-8 flex pr-2 pt-4 sm:-ml-10 sm:pr-4">
                      <button
                        type="button"
                        className="relative rounded-md text-gray-300 hover:text-white focus:outline-none focus:ring-2 focus:ring-white"
                        onClick={onClose}
                      >
                        <span className="absolute -inset-2.5" />
                        <span className="sr-only">Close panel</span>
                        <XMarkIcon className="size-6" aria-hidden="true" />
                      </button>
                    </div>
                  </Transition.Child>
                  <div className="flex h-full flex-col overflow-y-scroll bg-white py-6 shadow-xl">
                    <div className="px-4 sm:px-6">
                      <Dialog.Title className="text-2xl font-bold leading-6 text-gray-900">
                        {title}
                      </Dialog.Title>
                    </div>
                    <div className="relative flex-1 px-4 sm:px-6">
                      <div className="h-[calc(100%-100px)] w-full p-4">
                        {' '}
                        {/* Adjusted height */}
                        <Position3DPlot
                          currentBahnPoseIst={currentBahnPoseIst}
                          currentBahnPoseTrans={currentBahnPoseTrans}
                          idealTrajectory={idealTrajectory}
                          isTransformed={isTransformed}
                        />
                      </div>
                      {children}
                    </div>
                  </div>
                </Dialog.Panel>
              </Transition.Child>
            </div>
          </div>
        </div>
      </Dialog>
    </Transition.Root>
  );
};

export default SlideOver;
