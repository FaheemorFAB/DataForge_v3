import Head from "next/head";
import { useRouter } from "next/router";

type LegacyTemplateFrameProps = {
  src: string;
  title: string;
};

export default function LegacyTemplateFrame({ src, title }: LegacyTemplateFrameProps) {
  const router = useRouter();
  const query = router.asPath.includes("?") ? router.asPath.slice(router.asPath.indexOf("?")) : "";
  const frameSrc = `${src}${query}`;

  return (
    <>
      <Head>
        <title>{title}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>
      <iframe
        title={title}
        src={frameSrc}
        style={{
          position: "fixed",
          inset: 0,
          width: "100vw",
          height: "100vh",
          border: 0,
          background: "#050505"
        }}
      />
    </>
  );
}
