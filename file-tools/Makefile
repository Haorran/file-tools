FNPACK := $(realpath ../fnpack)
MANIFEST := manifest
OUTDIR := ..

.PHONY: build clean release

build:
	@app=$$(grep '^appname' $(MANIFEST) | sed 's/.*=\s*//' | tr -d ' '); \
	ver=$$(grep '^version' $(MANIFEST) | sed 's/.*=\s*//' | tr -d ' '); \
	echo "Building $$app v$$ver ..."; \
	cd frontend && npm run build && cd ..; \
	"$(FNPACK)" build -d .; \
	mv $$app.fpk $(OUTDIR)/$${app}_$${ver}.fpk; \
	echo "✅ $(OUTDIR)/$${app}_$${ver}.fpk"

bump:
	@old=$$(grep '^version' $(MANIFEST) | sed 's/.*=\s*//' | tr -d ' '); \
	new=$$(echo $$old | awk -F. '{printf "%d.%d.%d",$$1,$$2,$$3+1}'); \
	echo "Bumping version $$old -> $$new"; \
	sed -i '' "s/^version[[:space:]]*=.*/version        = $$new/" $(MANIFEST)

release: bump build

clean:
	rm -f $(OUTDIR)/file-tools_*.fpk
