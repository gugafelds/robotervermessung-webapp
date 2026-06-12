/* eslint-disable react/button-has-type */
/* eslint-disable jsx-a11y/no-static-element-interactions */

'use client';

import { ChartBarIcon, DocumentTextIcon } from '@heroicons/react/24/outline';
import ErrorIcon from '@heroicons/react/24/outline/FaceFrownIcon';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import React, { useState } from 'react';

import { Typography } from '@/src/components/Typography';
import { formatDate, formatNumber } from '@/src/lib/functions';
import { useTrajectory } from '@/src/providers/trajectory.provider';

interface InfoRowProps {
  label: string;
  value: React.ReactNode;
  singleColumn?: boolean;
}

const InfoRow: React.FC<InfoRowProps> = ({
  label,
  value,
  singleColumn = false,
}) => (
  <div
    className={`border-b border-gray-200 py-2 text-base ${
      singleColumn ? 'flex flex-col' : 'flex justify-between'
    }`}
  >
    <span className="font-medium">{singleColumn ? `${label}:` : label}</span>
    <span
      className={`font-semibold text-primary ${singleColumn ? 'mt-1' : ''}`}
    >
      {value}
    </span>
  </div>
);

interface InfoSectionProps {
  title: string;
  children: React.ReactNode;
}

interface TrajectoryInfoProps {}

const InfoSection: React.FC<InfoSectionProps> = ({ title, children }) => (
  <div className="mb-5 rounded-lg border border-l-4 border-primary bg-white p-4">
    <h3 className="mb-4 text-xl font-bold text-primary">{title}</h3>
    {children}
  </div>
);

export const TrajectoryInfo: React.FC<TrajectoryInfoProps> = () => {
  const { currentTrajInfo } = useTrajectory();
  const { currentTrajMetadata } = useTrajectory();
  const pathname = usePathname();

  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const selectedMeta =
    selectedId && selectedId !== currentTrajInfo!.trajID
      ? currentTrajMetadata?.segments.find((s) => s.segID === selectedId)
      : currentTrajMetadata?.trajectory;

  // Prüfe, ob wir uns auf der Auswertungsseite befinden
  const isOnEvaluationPage = pathname.includes('/evaluation');

  if (currentTrajInfo === null) {
    return (
      <span className="flex h-full min-w-80 flex-row justify-center border-r border-gray-500 bg-gray-50 p-4 lg:h-fullscreen lg:overflow-scroll">
        <Typography as="h5">No trajectory found</Typography>
        <span>
          <ErrorIcon className="mx-2 my-0.5 w-6 text-primary" />
        </span>
      </span>
    );
  }

  return (
    <div className="flex h-full min-w-80 flex-col border-r border-gray-500 bg-gray-50 p-3 lg:h-fullscreen lg:overflow-scroll">
      {currentTrajInfo && Object.keys(currentTrajInfo).length !== 0 && (
        <>
          <div className="rounded-xl p-4 text-primary ">
            <div className="text-sm font-medium">ID</div>
            <div className="relative">
              <button
                className="cursor-pointer text-2xl font-bold hover:underline"
                onClick={() => setDropdownOpen((prev) => !prev)}
              >
                {selectedId || currentTrajInfo.trajID || '-'}
              </button>
              {dropdownOpen && currentTrajMetadata && (
                <div className="absolute z-10 mt-1 rounded-lg border border-gray-200 bg-white shadow-md">
                  <button
                    className="cursor-pointer px-4 py-2 text-lg hover:bg-gray-100"
                    onClick={() => {
                      setSelectedId(currentTrajInfo.trajID);
                      setDropdownOpen(false);
                    }}
                  >
                    {currentTrajInfo.trajID}
                  </button>
                  {currentTrajMetadata.segments.map((seg) => (
                    <button
                      key={seg.segID}
                      className="cursor-pointer px-4 py-2 text-lg hover:bg-gray-100"
                      onClick={() => {
                        setSelectedId(seg.segID);
                        setDropdownOpen(false);
                      }}
                    >
                      {seg.segID}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <div className="pt-2">
              <div className="text-sm font-medium">Filename</div>
              <div className="text-xl font-semibold">
                {currentTrajInfo.recordFilename || '-'}
              </div>
            </div>

            {/* Kontextabhängiger Button */}
            <div className="my-2 flex w-fit rounded-lg bg-primary px-4 py-1 font-medium text-white transition duration-300 ease-in-out hover:bg-gray-800">
              {currentTrajInfo && (
                <Link
                  href={
                    isOnEvaluationPage
                      ? `/motion/${currentTrajInfo.trajID}`
                      : `/evaluation/${currentTrajInfo.trajID}`
                  }
                  className="flex items-center"
                >
                  {isOnEvaluationPage ? (
                    <>
                      <DocumentTextIcon className="mr-2 size-5" />
                      <span>Motion</span>
                    </>
                  ) : (
                    <>
                      <ChartBarIcon className="mr-2 size-5" />
                      <span>Evaluation</span>
                    </>
                  )}
                </Link>
              )}
            </div>
          </div>

          <InfoSection title="General">
            <InfoRow
              label="Movement Type"
              value={selectedMeta?.movType || '-'}
            />
            <InfoRow
              label="Duration"
              value={`${selectedMeta?.duration || '-'} s`}
            />
            <InfoRow
              label="Length"
              value={`${formatNumber(selectedMeta?.length) || '-'} mm`}
            />
            <InfoRow
              label="Max. Velocity"
              value={`${formatNumber(selectedMeta?.maxVel) || '-'} mm/s`}
            />
            <InfoRow
              label="Max. Accel."
              value={`${formatNumber(selectedMeta?.maxAccel) || '-'} mm/s²`}
            />
            <InfoRow
              label="Load"
              value={`${formatNumber(selectedMeta?.weight) || '-'} kg`}
            />
            <InfoRow label="Robot" value={currentTrajInfo.robotModel || '-'} />
            <InfoRow
              label="Source (M)"
              value={currentTrajInfo.sourceDataAct || '-'}
            />
            <InfoRow
              label="Source (C)"
              value={currentTrajInfo.sourceDataCmd || '-'}
            />
            <InfoRow
              label="Start"
              value={
                currentTrajInfo.startTime
                  ? formatDate(currentTrajInfo.startTime)
                  : '-'
              }
            />
            <InfoRow
              label="End"
              value={
                currentTrajInfo.endTime
                  ? formatDate(currentTrajInfo.endTime)
                  : '-'
              }
            />
          </InfoSection>

          <InfoSection title="Number of points">
            <div className="mb-2 border-gray-200">
              <div className="text-lg font-semibold text-gray-600">
                Measured:
              </div>
              <InfoRow
                label="Pose"
                value={formatNumber(currentTrajInfo.numberPointsPoseAct) || '-'}
              />
              <InfoRow
                label="Velocity"
                value={formatNumber(currentTrajInfo.numberPointsVelAct) || '-'}
              />
              <InfoRow
                label="Acceleration"
                value={
                  formatNumber(currentTrajInfo.numberPointsAccelAct) || '-'
                }
              />
            </div>

            <div className="border-gray-200">
              <div className="text-lg font-semibold text-gray-600">
                Commanded:
              </div>
              <InfoRow
                label="Position"
                value={formatNumber(currentTrajInfo.numberPointsPosCmd) || '-'}
              />
              <InfoRow
                label="Orientation"
                value={
                  formatNumber(currentTrajInfo.numberPointsOrientCmd) || '-'
                }
              />
              <InfoRow
                label="Velocity"
                value={formatNumber(currentTrajInfo.numberPointsVelCmd) || '-'}
              />
              <InfoRow
                label="Acceleration"
                value={
                  formatNumber(currentTrajInfo.numberPointsAccelCmd) || '-'
                }
              />
              <InfoRow
                label="Joint States"
                value={
                  formatNumber(currentTrajInfo.numberPointsJointStates) || '-'
                }
              />
              <InfoRow
                label="Setpoints"
                value={formatNumber(currentTrajInfo.numberSetpoints) || '-'}
              />
            </div>
          </InfoSection>

          <InfoSection title="Sample rates [Hz]">
            <div className="mb-2 border-gray-200">
              <div className="text-lg font-semibold text-gray-600">
                Measured:
              </div>
              <InfoRow
                label="Pose"
                value={formatNumber(currentTrajInfo.frequencyPoseAct) || '-'}
              />
              <InfoRow
                label="Velocity"
                value={formatNumber(currentTrajInfo.frequencyVelAct) || '-'}
              />
              <InfoRow
                label="Acceleration"
                value={formatNumber(currentTrajInfo.frequencyAccelAct) || '-'}
              />
            </div>

            <div className="border-gray-200">
              <div className="text-lg font-semibold text-gray-600">
                Commanded:
              </div>
              <InfoRow
                label="Position"
                value={
                  formatNumber(currentTrajInfo.frequencyPositionCmd) || '-'
                }
              />
              <InfoRow
                label="Orientation"
                value={
                  formatNumber(currentTrajInfo.frequencyOrientationCmd) || '-'
                }
              />
              <InfoRow
                label="Velocity"
                value={formatNumber(currentTrajInfo.frequencyVelCmd) || '-'}
              />
              <InfoRow
                label="Acceleration"
                value={formatNumber(currentTrajInfo.frequencyAccelCmd) || '-'}
              />
              <InfoRow
                label="Joint States"
                value={
                  formatNumber(currentTrajInfo.frequencyJointStates) || '-'
                }
              />
            </div>
          </InfoSection>
        </>
      )}
    </div>
  );
};
