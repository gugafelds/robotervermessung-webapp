export const formatDate = (dateString: string) => {
  const date = new Date(dateString);
  const day = date.getDate();
  const month = date.getMonth() + 1;
  const year = date.getFullYear();
  const hours = date.getHours();
  const minutes = date.getMinutes();
  const seconds = date.getSeconds();
  return `${day.toString().padStart(2, '0')}.${month
    .toString()
    .padStart(2, '0')}.${year} ${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
};

export const camelToWords = (str: string) =>
  str
    .replace(/([A-Z])/g, ' $1')
    .trim()
    .replace(/^\w/, (c) => c.toUpperCase());

export const getDataToBeDisplayed = (object: object, dataIncluded: string[]) =>
  Object.keys(object).filter((data) => dataIncluded.includes(data));

export const isDateString = (value: unknown) => {
  const regex = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{6}$/;
  return regex.test(value as string);
};

export const formatNumber = (
  num: number | null | undefined | unknown,
): string | number => {
  if (
    num === undefined ||
    num === null ||
    Array.isArray(num) ||
    Number.isNaN(num as number)
  ) {
    return '-'; // or return an empty string '' if you prefer
  }
  if (typeof num !== 'number') {
    return '-';
  }
  if (Number.isInteger(num)) {
    return num;
  }
  return num.toFixed(2);
};

export const json = (data: unknown) => JSON.parse(JSON.stringify(data));

export const filterBy = (filter: string, properties: string[]) => {
  return properties.some((property) => property.toLowerCase().includes(filter));
};
