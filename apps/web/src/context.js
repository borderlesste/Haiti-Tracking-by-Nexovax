import { createContext, useContext } from "react";
export const AppContext = createContext({});
export const Locale = createContext({ lang: "es", t: (key) => key });
export const useApp = () => useContext(AppContext);
export const useLocale = () => useContext(Locale);
