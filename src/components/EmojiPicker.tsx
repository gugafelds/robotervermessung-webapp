import EmojiPicker, { Categories } from 'emoji-picker-react';
import React from 'react';

import { Typography } from '@/src/components/Typography';

type EmojiPickerProps = {
  emoji: string;
  setEmoji: (emoji: string) => void;
};

export const EmojiPickerComponent = ({ emoji, setEmoji }: EmojiPickerProps) => {
  return (
    <>
      <Typography as="h4" className="mb-2 font-light">
        Select a Emoji
      </Typography>

      {emoji && (
        <button
          onClick={() => setEmoji('')}
          type="button"
          className="flex items-center rounded-md border-2 border-gray-200 p-3 hover:bg-gray-100"
        >
          <Typography as="h1" className="text-6xl">
            {emoji}
          </Typography>
        </button>
      )}

      <EmojiPicker
        open={!emoji}
        previewConfig={{ showPreview: false }}
        width="100%"
        height="70vh"
        lazyLoadEmojis
        onEmojiClick={({ emoji: e }) => setEmoji(e)}
        categories={[
          {
            category: Categories.TRAVEL_PLACES,
            name: 'Travel & Places',
          },
          {
            category: Categories.ACTIVITIES,
            name: 'Activities',
          },
          {
            category: Categories.SMILEYS_PEOPLE,
            name: 'Smileys & People',
          },
          {
            category: Categories.ANIMALS_NATURE,
            name: 'Animals & Nature',
          },
          {
            category: Categories.FOOD_DRINK,
            name: 'Food & Drink',
          },
          {
            category: Categories.OBJECTS,
            name: 'Objects',
          },
          {
            category: Categories.SYMBOLS,
            name: 'Symbols',
          },
          {
            category: Categories.FLAGS,
            name: 'Flags',
          },
        ]}
      />
    </>
  );
};
