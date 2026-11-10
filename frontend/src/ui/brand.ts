import dark1 from '../assets/brand/formpublisher.webp';
import dark2 from '../assets/brand/formpublisher@2x.webp';
import light1 from '../assets/brand/formpublisher-light.webp';
import light2 from '../assets/brand/formpublisher-light@2x.webp';

const NAME = 'formpublisher';

function img(cls: string, one: string, two: string, size: number, label: string): string {
  return `<img class="fp-mark ${cls}" src="${one}" srcset="${one} 1x, ${two} 2x" width="${size}" height="${size}" alt="${label}" draggable="false" decoding="async">`;
}

export function brandMark(size: number, label = NAME): string {
  return img('fp-art-dark', dark1, dark2, size, label) + img('fp-art-light', light1, light2, size, label);
}
