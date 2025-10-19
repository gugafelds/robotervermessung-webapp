import { Typography } from '@/src/components/Typography';

interface AccuracyCardProps {
  medianSIDTW?: number;
  meanSIDTW?: number;
}

export function AccuracyCard({ medianSIDTW, meanSIDTW }: AccuracyCardProps) {
  return (
    <div className="rounded-lg border bg-white p-4 shadow-md">
      <Typography as="h5">Durchschnittliche Genauigkeit</Typography>

      <div className="mt-3 grid grid-cols-2">
        {/* Median */}
        <div>
          <p className="text-sm text-gray-600">Median</p>
          <Typography as="h4" className="text-primary">
            {medianSIDTW !== undefined && medianSIDTW !== null
              ? `${medianSIDTW.toFixed(2)} mm`
              : 'N/A'}
          </Typography>
        </div>

        {/* Mean */}
        <div>
          <p className="text-sm text-gray-600">Mittelwert</p>
          <Typography as="h4" className="text-primary">
            {meanSIDTW !== undefined && meanSIDTW !== null
              ? `${meanSIDTW.toFixed(2)} mm`
              : 'N/A'}
          </Typography>
        </div>
      </div>
    </div>
  );
}
