'use client';

import { useEffect, useState } from 'react';

import { getTagInfo } from '@/src/actions/dashboard.service';

interface TagInfo {
  tag: string;
  robot: string;
  type: string;
  plane: string;
  vel_min: number | null;
  vel_max: number | null;
  stop_point: number | null;
  reorientation_xy: string;
  reorientation_z: string;
  min_distance: string;
  ws_x_min: number | null;
  ws_x_max: number | null;
  ws_y_min: number | null;
  ws_y_max: number | null;
  ws_z_min: number | null;
  ws_z_max: number | null;
  comment: string | null;
}

interface Props {
  selectedTags: string[];
}

function row(label: string, value: string | number | null | undefined) {
  if (value == null) return null;
  return (
    <div className="flex justify-between gap-4 border-b border-gray-100 py-1 text-sm last:border-0">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium text-gray-900">{value}</span>
    </div>
  );
}

export function TagInfoCard({ selectedTags }: Props) {
  const [infos, setInfos] = useState<TagInfo[]>([]);

  useEffect(() => {
    if (selectedTags.length === 0) { setInfos([]); return; }
    getTagInfo(selectedTags).then((r) => setInfos((r as { tags: TagInfo[] }).tags ?? []));
  }, [selectedTags]);

  if (selectedTags.length === 0 || infos.length === 0) return null;

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
      {infos.map((info) => (
        <div key={info.tag} className="rounded-2xl border border-gray-500 bg-white p-4">
          <p className="mb-3 text-lg font-bold text-blue-950">{info.tag}</p>
          <div className="space-y-0">
            {row('Robot', info.robot)}
            {row('Type', info.type)}
            {row('Plane', info.plane)}
            {row('Velocity', info.vel_min != null && info.vel_max != null ? `${info.vel_min}–${info.vel_max} mm/s` : null)}
            {row('Stop point', info.stop_point)}
            {row('Reorientation XY', info.reorientation_xy ? `${info.reorientation_xy}°` : null)}
            {row('Reorientation Z', info.reorientation_z ? `${info.reorientation_z}°` : null)}
            {row('Min distance', info.min_distance ? `${info.min_distance} mm` : null)}
            {row('Workspace X', info.ws_x_min != null && info.ws_x_max != null ? `${info.ws_x_min}–${info.ws_x_max} mm` : null)}
            {row('Workspace Y', info.ws_y_min != null && info.ws_y_max != null ? `${info.ws_y_min}–${info.ws_y_max} mm` : null)}
            {row('Workspace Z', info.ws_z_min != null && info.ws_z_max != null ? `${info.ws_z_min}–${info.ws_z_max} mm` : null)}
            {info.comment && row('Comment', info.comment)}
          </div>
        </div>
      ))}
    </div>
  );
}
