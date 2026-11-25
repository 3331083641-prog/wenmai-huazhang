import { projectBrand } from './projectBrand';
import heritageExterior from '../../../docs/screenshots/current/heritage-gallery.jpg';
import heritageInterior from '../../../docs/screenshots/current/heritage-interior.jpg';
import heritageDusk from '../../../docs/screenshots/current/heritage-dusk.jpg';
import paintingWorld from '../../../docs/screenshots/current/painting-world.jpg';

const previews = import.meta.glob<string>(
  '../../../docs/screenshots/{current,competition}/{creation-workspace,creative-products,culture-card,gallery,interactive-artwork,story-reading}.jpg',
  { eager: true, import: 'default' },
);
const folder = `../../../docs/screenshots/${projectBrand.previewFolder}`;

export const uiPreviews = {
  creator: previews[`${folder}/creation-workspace.jpg`],
  products: previews[`${folder}/creative-products.jpg`],
  cultureCard: previews[`${folder}/culture-card.jpg`],
  gallery: previews[`${folder}/gallery.jpg`],
  heritageExterior,
  heritageInterior,
  heritageDusk,
  experience: previews[`${folder}/interactive-artwork.jpg`],
  story: previews[`${folder}/story-reading.jpg`],
  paintingWorld,
};
