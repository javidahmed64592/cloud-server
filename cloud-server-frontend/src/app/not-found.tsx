// import Image from "next/image";

export default function NotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center space-y-8 text-center">
      {/* Logo */}
      <div className="mb-8 flex items-center space-x-4">
        {/* <Image
          src="/logo.svg"
          alt="Cloud Server Logo"
          width={64}
          height={64}
          priority
        /> */}
        <div className="text-2xl font-bold text-text-primary">Cloud Server</div>
      </div>

      {/* Error Message */}
      <div className="space-y-4">
        <h1 className="text-6xl font-bold text-neon-red">404</h1>
        <h2 className="text-2xl font-semibold text-text-primary">
          Page Not Found
        </h2>
        <div className="mx-auto max-w-md space-y-2">
          <p className="text-text-secondary">
            The page you&apos;re looking for doesn&apos;t exist.
          </p>
          <p className="text-text-secondary">
            It might have been moved, deleted, or never existed.
          </p>
        </div>
      </div>
    </div>
  );
}
