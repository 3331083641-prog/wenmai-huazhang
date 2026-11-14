import metadata from '../../metadata.json';

if (!Object.hasOwn(metadata.brandProfiles, metadata.name)) {
  throw new Error(`Unknown project brand: ${metadata.name}`);
}
const name = metadata.name as keyof typeof metadata.brandProfiles;
const profile = metadata.brandProfiles[name];

export const projectBrand = {
  name,
  ...profile,
  fullName: `${name}——${profile.subtitle}`,
};
