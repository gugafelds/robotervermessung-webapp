'use client';

export const ApplyFréchetButton = () => {
  return (
    <div className="mb-5 flex flex-wrap gap-3 rounded-3xl bg-stone-200">
      <div className="mt-3 text-lg font-bold text-primary">
        fréchet distance
      </div>

      <button
        type="button"
        className="flex items-center gap-2 rounded-xl bg-gray-300 p-2 text-lg font-extralight text-gray-500 shadow-md"
        onClick={async () => {}}
      >
        generate
      </button>
    </div>
  );
};
