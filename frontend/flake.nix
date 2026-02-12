{
  description = "Web development shell with Node.js, Bun, and Tailwind LSP";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = {nixpkgs, ...}:
  let
    system = "x86_64-linux";
    pkgs = nixpkgs.legacyPackages.${system};
    shell = pkgs.mkShell {
      nativeBuildInputs = with pkgs; [
        nodejs
        bun
        yarn
        pnpm
        neovim
        nushell
        starship
        tailwindcss-language-server
      ];
      shellHook = ''
        export SHELL=$(which nu)
        echo "Welcome to the web development environment"
      '';
    };
  in {
    devShells.${system} = {
      default = shell;
      web-dev = shell; # -- Allow nix develop .#web-dev in template directory
    };
  };
}



