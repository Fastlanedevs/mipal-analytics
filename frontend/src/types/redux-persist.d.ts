declare module "redux-persist/integration/react" {
  import { PersistorState } from "redux-persist";
  import { ReactNode } from "react";

  interface PersistGateProps {
    loading?: ReactNode;
    persistor: PersistorState;
    children: ReactNode;
  }

  export function PersistGate(props: PersistGateProps): JSX.Element;
}
