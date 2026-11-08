/**
 * 语言上下文
 */
import React, { createContext, useContext, useState, ReactNode } from 'react';

type Locale = 'en' | 'zh-CN';
type Site = 'leetcode.com' | 'leetcode.cn';

interface LocaleContextType {
  locale: Locale;
  site: Site;
  setLocale: (locale: Locale) => void;
  setSite: (site: Site) => void;
  toggleLocale: () => void;
}

const LocaleContext = createContext<LocaleContextType | undefined>(undefined);

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState<Locale>(() => {
    const saved = localStorage.getItem('locale');
    return (saved as Locale) || 'en';
  });

  const [site, setSite] = useState<Site>(() => {
    const saved = localStorage.getItem('site');
    return (saved as Site) || 'leetcode.com';
  });

  const handleSetLocale = (newLocale: Locale) => {
    setLocale(newLocale);
    localStorage.setItem('locale', newLocale);
  };

  const handleSetSite = (newSite: Site) => {
    setSite(newSite);
    localStorage.setItem('site', newSite);
  };

  const toggleLocale = () => {
    const newLocale = locale === 'en' ? 'zh-CN' : 'en';
    handleSetLocale(newLocale);
  };

  return (
    <LocaleContext.Provider
      value={{
        locale,
        site,
        setLocale: handleSetLocale,
        setSite: handleSetSite,
        toggleLocale,
      }}
    >
      {children}
    </LocaleContext.Provider>
  );
}

export function useLocale() {
  const context = useContext(LocaleContext);
  if (context === undefined) {
    throw new Error('useLocale must be used within a LocaleProvider');
  }
  return context;
}
