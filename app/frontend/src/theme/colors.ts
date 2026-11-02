// onBlue: texto sobre fondos `blue`; en oscuro el azul es claro y el blanco no tendría contraste.
export const palettes = {
  light: { background: '#F6F3EA', surface: '#FFFFFF', text: '#10304A', muted: '#53697D', blue: '#1262DC', onBlue: '#FFFFFF', pale: '#E6EFFD', border: '#D9E2EB', danger: '#B3303F', green: '#13705F' },
  dark: { background: '#091624', surface: '#12263A', text: '#E8F1FD', muted: '#A3BAD1', blue: '#7DB2FF', onBlue: '#06213F', pale: '#1A3C62', border: '#2B455B', danger: '#FF8D9C', green: '#6AD2C1' },
};
export type Palette = typeof palettes.light;
