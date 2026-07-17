import { createContext, useContext, useEffect, useState } from "react";

const LanguageContext = createContext();

export function LanguageProvider({ children }) {
  const [lang, setLangState] = useState(
    () => localStorage.getItem("lang") || "en"
  );

  function setLang(l) {
    setLangState(l);
    localStorage.setItem("lang", l);
  }

  // Keep the document element in sync so the browser applies the right
  // direction/lang to scrollbars, form controls and screen readers.
  useEffect(() => {
    document.documentElement.setAttribute("lang", lang);
    document.documentElement.setAttribute("dir", lang === "ar" ? "rtl" : "ltr");
  }, [lang]);

  return (
    <LanguageContext.Provider value={{ lang, setLang, isAr: lang === "ar" }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  return useContext(LanguageContext);
}
