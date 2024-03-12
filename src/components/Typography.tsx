import type { ForwardedRef, ReactNode } from 'react';
import React, { forwardRef } from 'react';

type Props<T extends keyof JSX.IntrinsicElements> = React.ComponentProps<T>;

type BaseTypographyProps = Props<'p'> &
  Props<'h1'> &
  Props<'h2'> &
  Props<'h3'> &
  Props<'h4'> &
  Props<'h5'> &
  Props<'h6'>;
export type TypographyProps = BaseTypographyProps & {
  as: 'p' | 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6';
  className?: string;
  children: ReactNode;
};

const TypographyComponent = (
  { as, className, children, ...rest }: TypographyProps,
  ref: ForwardedRef<HTMLElement>,
) => {
  let template;

  switch (as) {
    case 'h1':
      template = React.createElement(
        as,
        {
          ...rest,
          ref,
          className,
        },
        children,
      );
      break;
    case 'h2':
      template = React.createElement(
        as,
        {
          ...rest,
          ref,
          className,
        },
        children,
      );
      break;
    case 'h3':
      template = React.createElement(
        as,
        {
          ...rest,
          ref,
          className,
        },
        children,
      );
      break;
    case 'h4':
      template = React.createElement(
        as,
        {
          ...rest,
          ref,
          className,
        },
        children,
      );
      break;
    case 'h5':
      template = React.createElement(
        as,
        {
          ...rest,
          ref,
          className,
        },
        children,
      );
      break;
    case 'h6':
      template = React.createElement(
        as,
        {
          ...rest,
          ref,
          className,
        },
        children,
      );
      break;
    default:
      template = React.createElement(
        as,
        {
          ...rest,
          ref,
          className,
        },
        children,
      );
      break;
  }

  return template;
};

export const Typography = forwardRef(TypographyComponent);
