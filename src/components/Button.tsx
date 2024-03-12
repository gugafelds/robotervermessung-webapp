/* eslint-disable tailwindcss/no-custom-classname */
/* eslint-disable tailwindcss/classnames-order */
/* eslint-disable react/button-has-type */
import React, { type HTMLProps } from 'react';

type ButtonProps = HTMLProps<HTMLButtonElement> & {
  type: 'button' | 'submit' | 'reset';
  color: string;
};

export const Button = ({ color, label, ...props }: ButtonProps) => {
  return (
    <button
      {...props}
      type={props.type}
      className={`
      ${props.className}
        px-6 py-2.5 bg-${color} text-white font-medium text-xs leading-tight
        uppercase rounded shadow-md hover:bg-${color}-700 hover:shadow-lg
        focus:bg-${color}-700 focus:shadow-lg focus:outline-none focus:ring-0
        active:bg-${color}-800 active:shadow-lg transition duration-150
        ease-in-out`}
    >
      {label}
    </button>
  );
};
