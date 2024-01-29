{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-23.11";
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs {
        inherit system;
      };
      pythonEnv = pkgs.python3.withPackages (ps: [
        ps.requests
        ps.lxml
      ]);
    in {
      devShells.${system}.default = pkgs.mkShell {
        nativeBuildInputs = [ pythonEnv ];
      };
    };
}
