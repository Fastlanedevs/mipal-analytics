declare module "*.mp4" {
  const src: string;
  export default src;
}

interface Window {
  google: {
    accounts: {
      id: {
        initialize: (config: any) => void;
        renderButton: (element: HTMLElement | null, options: any) => void;
        prompt: () => void;
        disableAutoSelect: () => void;
      };
    };
  };
}
