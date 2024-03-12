import { type FC, type InputHTMLAttributes, type ReactElement } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string | ReactElement;
}

export const Input: FC<InputProps> = ({ label, value, onChange }) => (
  <div className="mb-4">
    <label
      htmlFor="firstName"
      className="mb-2 inline-block font-light text-gray-700"
    >
      {label}
    </label>
    <input
      type="text"
      className="m-0 block w-full
      rounded border border-solid border-gray-300
      bg-white bg-clip-padding px-3 py-1.5
      text-base font-normal text-gray-700 transition
      ease-in-out focus:border-blue-600 focus:bg-white
      focus:text-gray-700 focus:outline-none"
      value={value}
      onChange={onChange}
      id="firstName"
    />
  </div>
);
