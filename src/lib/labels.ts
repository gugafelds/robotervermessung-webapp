// Display names for the codes stored in the database (motion.traj_info: robot_model, source_data_act,
// source_data_cmd, path_planning). Only the visualisation changes, the stored values stay as they are.
const LABELS: Record<string, string> = {
  abb_irb4400: 'ABB IRB 4400',
  abb_irb4600: 'ABB IRB 4600',
  leica_at960: 'Leica AT960',
  abb_websocket: 'ABB WebSocket',
  abb_steuerung: 'ABB controller',
};

export const displayName = (code?: string | null): string =>
  code ? (LABELS[code] ?? code) : '-';

// Robot typed in a search ("irb4400", "abb irb4400", "IRB 4600", "abb_irb4600") -> robot_model code.
// Returns the code and the text without the robot part.
export const parseRobot = (text: string): { robot?: string; rest: string } => {
  const m = text.match(/(?:^|\s)(?:abb[\s_-]*)?irb[\s_-]*(\d{3,4})(?=\s|$)/i);
  if (!m) return { rest: text };
  return {
    robot: `abb_irb${m[1]}`,
    rest: `${text.slice(0, m.index)} ${text.slice((m.index ?? 0) + m[0].length)}`,
  };
};
