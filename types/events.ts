import type { ChangeEvent, FormEvent, MouseEvent } from 'react';

export type InputChangeEventHandler = ChangeEvent<HTMLInputElement>;
export type TextareaChangeEventHandler = ChangeEvent<HTMLTextAreaElement>;
export type SelectChangeEventHandler = ChangeEvent<HTMLSelectElement>;
export type ButtonEventHandler = MouseEvent<HTMLButtonElement>;

export type MouseEventHandler = MouseEvent<HTMLAnchorElement>;

export type FormEventHandler = FormEvent<HTMLFormElement>;

export type GenericEvent =
  | InputChangeEventHandler
  | TextareaChangeEventHandler
  | SelectChangeEventHandler
  | ButtonEventHandler
  | MouseEventHandler
  | FormEvent<HTMLInputElement>
  | MouseEvent<HTMLTextAreaElement>
  | MouseEvent<HTMLDivElement>
  | FormEventHandler;
