import type { ObjectId } from 'mongodb';
import type { Dispatch, SetStateAction } from 'react';

import { type GenericEvent } from '../../types/events';

export const formatDate = (dateString: string) => {
  const date = new Date(dateString);
  const day = date.getDate();
  const month = date.getMonth() + 1;
  const year = date.getFullYear();
  const hours = date.getHours();
  const minutes = date.getMinutes();
  return `${day.toString().padStart(2, '0')}.${month
    .toString()
    .padStart(2, '0')}.${year} ${hours.toString().padStart(2, '0')}:${minutes
    .toString()
    .padStart(2, '0')}`;
};

export const stopPropagationFn = (e: GenericEvent) => {
  e.stopPropagation();
};

export function updateSingleElement<T extends { _id?: ObjectId | string }>(
  elId: ObjectId | string,
  elementsArray: T[],
  setState: Dispatch<SetStateAction<T[]>>,
  fieldsToUpdate: Record<string, unknown>,
): void {
  const arrayCopy = [...elementsArray];
  const indexToUpdate = arrayCopy.findIndex(
    (el) => el?._id?.toString() === elId,
  );
  if (indexToUpdate >= 0) {
    const update = arrayCopy.map((el, index) => {
      if (index === indexToUpdate) {
        return {
          ...el,
          ...fieldsToUpdate,
        };
      }
      return el;
    });
    setState(update);
  }
}

export const json = (data: unknown) => JSON.parse(JSON.stringify(data));
