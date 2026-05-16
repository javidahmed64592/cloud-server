"use client";

// import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import HealthIndicator from "@/components/HealthIndicator";
import { useAuth } from "@/contexts/AuthContext";

const Navigation = () => {
  const pathname = usePathname();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const { logout, isAuthenticated } = useAuth();

  const navItems = [
    {
      name: "Drive",
      href: "/drive",
      active: pathname === "/drive/",
    },
  ];

  const toggleMenu = () => {
    setIsMenuOpen(!isMenuOpen);
  };

  const closeMenu = () => {
    setIsMenuOpen(false);
  };

  return (
    <nav className="sticky top-0 z-50 w-full border-b border-terminal-border bg-background-secondary">
      <div className="w-full px-4 sm:px-6 lg:px-8">
        <div className="flex items-center h-16 w-full justify-between">
          {/* Logo */}
          <div className="flex items-center space-x-4">
            <Link href="/" className="flex items-center space-x-3">
              {/* <Image
                src="/logo.svg"
                alt="Cloud Server Logo"
                width={32}
                height={32}
                className="neon-glow"
                priority
              /> */}
              <div className="flex flex-col">
                <div className="nav-logo-text text-xl font-bold text-text-primary sm:text-xl">
                  Cloud Server
                </div>
              </div>
            </Link>
            <HealthIndicator />
          </div>

          {/* Desktop Navigation Links */}
          <div className="hidden lg:flex flex-1 justify-end items-center space-x-1">
            {navItems.map(item => {
              const normalized = (pathname || "").replace(/\/$/, "") || "/";
              const isActive =
                normalized === item.href ||
                (item.href === "/drive" && normalized === "/");

              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`
                    rounded-md px-4 py-2 text-sm font-medium transition-all duration-200
                    ${
                      isActive
                        ? "font-bold text-border-accent"
                        : "text-text-secondary hover:bg-background-tertiary hover:text-text-primary"
                    }
                  `}
                >
                  {item.name}
                </Link>
              );
            })}
            {isAuthenticated && (
              <button
                onClick={logout}
                className="ml-4 rounded-md px-4 py-2 text-sm font-medium text-neon-red transition-all duration-200 hover:bg-background-tertiary"
              >
                Logout
              </button>
            )}
          </div>

          {/* Mobile Menu Button */}
          <div className="lg:hidden">
            <button
              onClick={toggleMenu}
              className="inline-flex items-center justify-center rounded-md p-2 text-text-secondary focus:outline-none focus:ring-2 focus:ring-inset focus:ring-border-accent hover:bg-background-tertiary hover:text-text-primary"
              aria-expanded="false"
            >
              <span className="sr-only">Open main menu</span>
              {/* Hamburger icon */}
              <svg
                className={`${isMenuOpen ? "hidden" : "block"} h-6 w-6`}
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              </svg>
              {/* Close icon */}
              <svg
                className={`${isMenuOpen ? "block" : "hidden"} h-6 w-6`}
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        </div>

        {/* Mobile Menu */}
        <div className={`lg:hidden ${isMenuOpen ? "block" : "hidden"}`}>
          <div className="mt-2 space-y-1 border-t border-terminal-border px-2 pb-3 pt-2 sm:px-3">
            {navItems.map(item => {
              const normalized = (pathname || "").replace(/\/$/, "") || "/";
              const isActive =
                normalized === item.href ||
                (item.href === "/drive" && normalized === "/");

              return (
                <Link
                  key={item.name}
                  href={item.href}
                  onClick={closeMenu}
                  className={`
                    block rounded-md px-3 py-2 text-base font-medium transition-all duration-200
                    ${
                      isActive
                        ? "bg-background-tertiary font-bold text-border-accent"
                        : "text-text-secondary hover:bg-background-tertiary hover:text-text-primary"
                    }
                  `}
                >
                  {item.name}
                </Link>
              );
            })}
            {isAuthenticated && (
              <button
                onClick={() => {
                  closeMenu();
                  logout();
                }}
                className="block w-full rounded-md px-3 py-2 text-left text-base font-medium text-neon-red transition-all duration-200 hover:bg-background-tertiary"
              >
                Logout
              </button>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
